# PNE 2026–2036 — macro-rodada de novas fontes

## Decisão

A rodada auditou Censo Escolar, INEC/ENEC, MUNIC, CAPES/Sucupira, CPC, Enade e
IGC. Foram homologadas cinco relações exclusivamente como `complementary`.
Seleção de direção, conectividade INEC, plano climático municipal e IGC
municipalizado ficaram fora da release. Nenhuma relação foi criada diretamente
como `progress`, nenhuma ausência foi convertida em zero e não há consulta
externa durante build ou runtime.

A release de entrada era
`68134c9254da62d2f04d2a1aea7764bab19bf5748278761ad0179198ff0a529a`,
com contrato 1.5.0 e política 1.3.0.

## Fontes auditadas

| Fonte | Edição | Decisão | Cobertura e motivo |
| --- | --- | --- | --- |
| Censo Escolar | 2025 | bloqueada | O dicionário documenta variáveis da tabela de gestor, mas o CSV público disponível contém 879 colunas da tabela de escola e não contém `QT_GEST_BAS_DIRETOR`, `QT_GEST_BAS_ACESSO_CARGO_SEL` nem `QT_GEST_BAS_ACESSO_CARGO_P_SEL`. Campo ausente não foi tratado como não atendimento. |
| INEC/ENEC | nota técnica vigente na auditoria | bloqueada | Não foi localizada base pública estruturada por escola com identificador estável, energia, conexão, velocidade adequada, Wi-Fi e estado monitorada/não monitorada. Internet declarada no Censo Escolar não foi usada como proxy. |
| MUNIC/IBGE | Educação 2021; clima 2024 | parcial | 497 municípios. Planos de carreira e fórum aprovados; plano climático bloqueado por ausência de variável compatível na edição 2024. |
| CAPES/Sucupira | 2024 | aprovada após correção territorial | 497 municípios; 425 programas-sede, 454 vínculos municipais reconciliados, 7.683 títulos e 35 municípios com oferta local. Em rede, a territorialidade é o município da IES à qual o discente está vinculado. |
| CPC | ciclo 2023 | aprovada | 652 cursos com faixa válida em 65 municípios. |
| Enade Licenciaturas | ciclo 2025 | aprovada | 4.236 participantes em resultados não suprimidos de 52 municípios; 22 participantes em resultados suprimidos permanecem desconhecidos. |
| IGC | ciclo 2023 | bloqueada | O arquivo oficial identifica IES e UF, mas não município da sede. A junção externa necessária não foi homologada. |

RAIS/Caged não integrou a auditoria, conforme o escopo da rodada.

## Snapshots oficiais e SHA-256

| Arquivo | Tamanho | SHA-256 |
| --- | ---: | --- |
| Censo Escolar 2025 — CSV auditado | 692.205.645 bytes | `db63218b145c44d970677b7e2f59c9b638c5433de6b8447fe0888cb87c0130b0` |
| Censo Escolar 2025 — dicionário | 226.363 bytes | `b39b0761ee7ad8c935e7140eb518d97713a5e5e604c4a70b877224f68d70416e` |
| INEC — `NotaTecnica.pdf` | 50.790 bytes | `2f148dd3633fd2561a27ae861072b57cf7763a37ba68e88e6d174ac215a48025` |
| MUNIC 2021 | 18.796.622 bytes | `cc3b942c2885798e767100766c3b2888e31d1eca42b796538af2cfc3e76edb4e` |
| MUNIC 2024 | 25.535.974 bytes | `93d9f836e4435df6429c642fa6897640a0f0e67b7946cf354bb04eded342bf01` |
| CAPES programas 2024 | 1.801.673 bytes | `9402aec8b2bfbf1d0b4d690511ba86f477f649e6f56f477ff747119a7dc67476` |
| CAPES metadados de programas | 175.733 bytes | `5ad3d2c23c8d71bb352a4efb122d636ed7a600aebf13b4cc43d5be8af0ca5db5` |
| CAPES discentes 2024 | 188.022.486 bytes | `b37737e9e9552f51ab8aaeb4fe53f281a95c1078e4ad295cbeb5c2561c65b566` |
| CAPES metadados de discentes | 182.669 bytes | `e1c28ec0ac28f65a52917077bdf258af1ebf1d03f59eba8fa78de3a472e522f2` |
| CPC 2023 | 3.080.363 bytes | `5bf616a7dd56445796f606c080c0462488418274db2828604b8bc39eedd71c3f` |
| Enade Licenciaturas 2025 | 546.797 bytes | `12e73c0603d388711f914dae9d8e3ea15b46aa56fde2a11b4634baa9e8417911` |
| IGC 2023 | 1.868.751 bytes | `92cd8f702e0e92f6d616e7b4bbf879e1c24b749392b05bc7ad149e00d80b4003` |

Hashes normalizados:

- MUNIC: `474f7ac0d39080d899a057e22734a5ae86ade397fa07d6ab3a4acc148a2a5c57`;
- CAPES: `1211982c91a501ea79fb70b00e192e633ed01f0518fbe9a9eb6dc8e6b5ea80b7`;
- CPC/Enade/IGC: `de88aa4bf61fb6e9a801e5c7372d019b3cdeb9a89a7593333b741f1b601da074`.

Os snapshots incorporados, manifestos, dicionários, políticas de ausência,
URLs oficiais e hashes ficam em `data_pipeline/data/pne_macro_sources`.

## Relações, fórmulas e ausência

| Relação | Fórmula | Disponível | Ausência segura |
| --- | --- | ---: | --- |
| `relation.17.c.munic_planos_carreira_declarados` | `I(MEDU16=Sim) + I(MEDU21=Sim)` | 497 | resposta desconhecida → `unavailable`; dois “Não” explícitos → zero observado |
| `relation.18.c.munic_forum_educacao_declarado` | `I(MEDU15=Sim)` | 497 | resposta desconhecida → `unavailable`; “Não” explícito → zero observado |
| `relation.16.a.capes_titulados_oferta_local` | mestres titulados + doutores titulados em programas com sede ou IES vinculada no município em 2024 | 35 | 462 sem sede, oferta vinculada ou linha de discente → `not_applicable`; oferta confirmada com zero título → zero observado; cobertura/territorialidade inconclusiva → `unavailable` |
| `relation.15.a.cpc_cursos_oferta_local` | `100 × cursos com CPC faixa 3–5 ÷ cursos com CPC válido` | 65 | 18 sem oferta local → `not_applicable`; 165 com oferta sem avaliação → `unavailable`; 249 com oferta desconhecida → `unavailable` |
| `relation.17.e.enade_licenciaturas_oferta_local` | `100 × concluintes no/above Padrão 1 ÷ participantes em resultados não suprimidos` | 52 | 18 sem oferta local → `not_applicable`; 178 sem avaliação → `unavailable`; 249 com oferta desconhecida → `unavailable`; suprimidos → unknown |

Todas são complementares, sem referência legal municipal, distância, status,
classificação, projeção ou referência estadual publicada. CPC e Enade preservam
organização acadêmica e categoria administrativa no snapshot. Não há média
simples municipal; a política de cada fórmula registra razão de somas apenas
como possibilidade de auditoria quando os componentes são aditivos.

## Contrato e política

- contrato 1.6.0, com 51 indicadores, 51 relações, 14 fontes e 51 fórmulas;
- hash normalizado do contrato:
  `758438f2d1c508800b29a8db991d25ec0a18ec9cf63bab8a5a4df349d80e30a6`;
- política editorial 1.4.0, com 42 relações visíveis;
- hash normalizado da política:
  `57a59d6b7284728074812e0555392bccd1169404d0c7f9eb94d345d2b6285fa8`;
- os cinco indicadores da macro-rodada são V3-only e não foram inseridos no
  catálogo/materialização V2.

## Staging, diff e promoção

Foram gerados dois stagings completos. Para reproduzir a comparação, use
diretórios efêmeros configurados por `--output-dir`, por exemplo
`data_pipeline/export/pne-v3-macro-a` e
`data_pipeline/export/pne-v3-macro-b`; caminhos locais de uma estação de
trabalho não integram o registro metodológico.

Os 498 arquivos de cada staging — manifesto e 497 municípios — são idênticos
byte a byte. O SHA-256 do manifesto de staging é
`e5b6d900c4ac3efa61f7b96d8bc22e85c7c2607befc9feedad2f46bf9a54831e`.

O diff registro a registro contra a release anterior:

- preservou 16.127 registros;
- alterou zero registro existente;
- removeu zero registro;
- acrescentou 1.145 registros, todos pertencentes às cinco relações novas;
- alterou apenas os 497 resumos municipais, além das versões e hashes do
  envelope/manifesto.

Depois da release original da macro-rodada, uma release corretiva adicional
foi promovida para reconciliar a territorialidade CAPES:

- release/`aggregateHash`:
  `cebc9af2f51cfc779598a930e9ead348cd7463cc8d186b156c89bba4e4d88131`;
- hash semântico:
  `575bade9388b72b87a85606fe0eb6d4f26d396e2c90c37a0ce8dfb97ac4b1b3b`;
- SHA-256 do manifesto da release:
  `bab4f13867b69efe2c87c7603143f3a7aa48a7d89b8fb17ce75d29a7275e066a`;
- SHA-256 de `current.json`:
  `ce8198816a3203d04035e427cb028569dc27cff5cd3f21551a84a80135e92d13`.

Os dois stagings corretivos, com 498 arquivos idênticos byte a byte, são
`C:\tmp\pne-diagnostic-v3-staging-capes-fix-final-a` e
`C:\tmp\pne-diagnostic-v3-staging-capes-fix-final-b`. O SHA-256 do manifesto
de staging é
`92eef3984f7df4638a2e55d7a5bd4a3afabf40d2648d9be8581ce79c12ea7628`.
Contra a release anterior, somente
`relation.16.a.capes_titulados_oferta_local` mudou em 35 municípios; somente o
resumo de Jaguari mudou, e todas as demais relações permaneceram idênticas.

## Contagens finais

- 497 municípios;
- 17.273 resultados;
- 10.155 `progress` e 7.118 `complementary`;
- 8.663 `advance`, 1.492 `maintain` e 0 `unclassified`;
- 4.466 `essential` e 12.807 `standard`;
- mínimo/máximo municipal de 28/40;
- 526 valores numéricos acima de 100;
- 961 ocorrências `hidden` excluídas;
- zero duplicidade, arquivo inválido, `NaN` ou `Infinity`.

## Interface e preservação

Os complementares usam visual neutro e não mostram status, distância, meta ou
projeção. “Fonte e cálculo” permanece recolhido. Resultados `not_applicable`
não criam card grande vazio. A inspeção em 1280 × 720 e 390 × 844 confirmou os
cinco cards em Alegrete, ausência de overflow horizontal, disclosure recolhido
e nenhum aviso ou erro de navegador. São Pedro da Serra confirmou a omissão do
card CAPES em estado `not_applicable`. Após a correção, Jaguari confirmou 24
títulos no card CAPES, a territorialidade da IES vinculada em programas em
rede, visual neutro e ausência de overflow horizontal nos mesmos viewports.

A mídia de impressão gerou PDF A4 válido com os cinco resultados, sem status,
meta ou distância nos complementares. O Relatório Técnico Municipal e o
workbook foram validados pelo teste educacional; a coluna de situação fica
vazia para relações complementares, enquanto fonte e metodologia são
preservadas.

As releases anteriores `3832c341...`, `b1780788...`, `8378537c...`,
`68134c92...` e `818635ea...` permanecem presentes. O conjunto V2 manteve,
antes e depois da rodada, o SHA-256
`ae184e57c56b79a55c667db951275036bef6fad45a558b5dd2cb908ed1a834dc`.
Não houve commit nem push.
