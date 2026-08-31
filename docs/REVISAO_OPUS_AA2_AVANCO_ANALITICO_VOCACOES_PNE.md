# Reconciliação Opus AA2 — avanço analítico Vocações × PNE

**Classificação:** `DATA_LOGIC`
**Primeira auditoria:** `AT_RISK`, confiança `0,68`
**Reauditoria limitada:** `ON_TRACK`, confiança `0,80`
**SHA-256 da reauditoria:** `74585729780496bd4c20f5b0d12d50b4243f268539a167538db8a8093af28e54`
**Resultado guardado:** `.tmp/codex-analytics-program/aa2-opus-results/opus-result.json`
**SHA-256:** `cfa6d8442e4aea5dd4d900405617b15f63d5fa53beddf0ef1fe0d8e0625ec416`

## Decisão

A auditoria não detectou erro de cálculo. Ela identificou três riscos altos de
interpretação e promoção, além de lacunas de documentação e testes. Nenhum estimador,
p-valor, regra terminal ou família BH foi alterado. As correções aceitas são guardas
de linguagem, promoção, proveniência, amostra, potência e auditabilidade.

O pacote reconciliado preserva as 49 linhas de resultados, 86 de robustez, 5.574 de
heterogeneidade, 51 comparações de escopo, 26 p-valores válidos em 27 slots e os oito
estados terminais originais. Seu digest analítico é
`b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879`.

Este documento é o registro canônico da reconciliação AA2. Os hashes deste arquivo, do
relatório e do histórico são publicados separadamente em
`docs/RECIBO_DOCUMENTAL_AA2_AVANCO_ANALITICO_VOCACOES_PNE.json`, evitando o problema
de um documento tentar conter o próprio hash.

## Achados altos

| Achado Opus | Avaliação | Resolução |
| --- | --- | --- |
| P7 parecia “negativo” apenas após BH, apesar de p exato bruto `0,039` e sinais estáveis | aceito | O registry explicita os seis membros da família `MF_P7_RURALITY_INCLUSION`; cada linha carrega a família. O claim diz “não significativo após o ajuste familiar conservador pré-registrado”, conserva BH `0,117`, declara o intervalo aproximado não primário e proíbe leitura de ausência. O estado terminal não mudou. |
| P1 não ganhou capacidade preditiva sobre o baseline e usa banda ampla | aceito | O claim serializa RMSE completo `1,721727`, baseline `1,715818`, diferença, razão resíduo/banda, sinais dos três ajustes e `nonFlaggingIsEvidenceOfTypicality=false`. A promoção exige o teto de comparação contextual. |
| A alternativa P8 por matrícula compartilha denominador/escala e poderia ser promovida isoladamente | aceito | A linha recebeu `BLOCKED_DENOMINATOR_CONSTRUCTION_AND_TERMINAL_INSUFFICIENT`; o claim explica a construção compartilhada, mantém o principal ajustado pela escala e bloqueia toda promoção independente de P8. |

## Achados médios

| Achado Opus | Avaliação | Resolução |
| --- | --- | --- |
| 5.574 linhas de heterogeneidade sem teto inferencial | aceito | Todas têm `EXPLORATORY_NO_INFERENCE`, `NOT_APPLICABLE_EXPLORATORY` e `BLOCKED_FROM_MANAGER_FACING`. Um controle QA verifica 100% das linhas. |
| Histórico do pré-registro e correção mecânica do registro externo | aceito com limite | Foi criado `REGISTRO_HISTORICO_PRE_REGISTRO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.md`, com hashes de `1.0.1`, `1.0.2`, `1.0.3`, probes e auditorias. Não existe commit/timestamp externo retroativo; essa limitação fica explícita e nenhuma versão `1.0.0` foi inventada. |
| N/G e conflito entre intervalo aproximado e teste exato em P4/P7 | aceito | Cada ajuste serializa `analytic_sample_n`, `cluster_count`, estado de G e primazia do intervalo. P4/P7 marcam `APPROXIMATE_NON_PRIMARY_EXACT_SIGN_P_PRIMARY`. |
| Calcular mínimo efeito detectável em resultados negativos | parcialmente aceito | A preocupação de baixa potência foi aceita. Um MDE pós-hoc não foi adicionado porque não constava do pré-registro; todas as linhas registram `NOT_PREREGISTERED_NOT_COMPUTED`, e P4/P6/P7 carregam `LOW_POWER_NO_ABSENCE_CLAIM`. |
| P2 não nomeava série/vintage nem risco de rebase | aceito com limite | O claim identifica `public.populacao_idade.pop_estimada`, snapshot e hash. A vintage não existe no snapshot congelado; fica `UNRESOLVED_IN_FROZEN_LOCAL_SNAPSHOT`. O componente de relação é declarado resíduo da identidade, capaz de absorver revisões/rebases, mobilidade e cobertura. Não houve sensibilidade inventada. |
| Determinismo parecia depender de igualar manifestos depois do cálculo | aceito | O manifesto declara que a prova cobre os seis artefatos analíticos não-manifesto, que cada candidato registra seu seed e que o manifesto final normaliza ambos numa evidência comum. O teste verifica esses campos. |
| Relatório e reconciliação ausentes no pacote apresentado ao auditor | aceito | O relatório AA2 existia logo após a preparação do primeiro pacote; esta reconciliação e o histórico agora completam a evidência documental. |

## Achados baixos

| Achado Opus | Avaliação | Resolução |
| --- | --- | --- |
| CBO de dois dígitos pode inflar correspondência | aceito | P5 declara `CBO_TWO_DIGIT_SUBGROUP`, teto de correspondência e `fourDigitSensitivityState=NOT_SUPPORTED_BY_FROZEN_BRIDGE`. |
| Finanças nominais inseguras entre anos | aceito | O claim P8 proíbe comparação temporal nominal; cada cross-section permanece separado. |
| Notebook não está no gate de dois processos | aceito | O notebook é acompanhante de auditoria, não fonte nem artefato autoritativo. Ele verifica valores serializados, mas a prova determinística permanece no pacote transacional. |

## Lacunas factuais do primeiro pacote de evidências

Alguns itens marcados como ausentes já existiam, mas não foram incluídos no pacote
curto enviado ao Opus:

- o pré-registro já continha o mapa exato das cinco famílias e 27 slots;
- os oito claims e seus tetos já eram serializados em `CLAIMS_AA2.json`;
- `total_all_dependencies` já estava fixado no contrato, pré-registro, painel e probe;
- a ponte curso–CBO já carregava hash, cobertura e reconciliação;
- o relatório AA2 foi criado após a montagem do primeiro pacote de auditoria.

Esses pontos não foram tratados como erro metodológico. Na reconciliação, passaram a
ser expostos também nos artefatos consumíveis e no próximo pacote Opus.

## Mapa completo de multiplicidade

O registry em `CLAIMS_AA2.json` publica os 27 slots das cinco famílias. Vinte e seis
têm p inferencial válido; `P8_ALT_2024_SIZE_ADJUSTED` é o único fit inválido e conserva
p bruto/BH nulos, embora ocupe internamente o slot fixo com p=1.

| Família | Slots pré-registrados |
| --- | --- |
| `MF_P3_SCHOOL_CONDITIONS` | `P3_MAIN_DROPOUT_L0`; `P3_ALT_FAILURE_L0`; `P3_ALT_DROPOUT_L1`; `P3_SENS_EXCLUDE_2020_2021`; `P3_SENS_WINDOW_2022_2025`; `P3_PLACEBO_LEAD1`; `P3_SENS_EXCLUDE_VALE_10` |
| `MF_P4_YOUTH_WORK` | `P4_MAIN_L0`; `P4_ALT_L1`; `P4_ALT_L2`; `P4_SENS_EXCLUDE_2020_2021`; `P4_PLACEBO_LEAD1`; `P4_REVERSE_DIRECTION` |
| `MF_P6_ADULT_EJA_WORK` | `P6_EJA_SPEARMAN`; `P6_WORK_SPEARMAN`; `P6_EJA_PEARSON`; `P6_WORK_PEARSON` |
| `MF_P7_RURALITY_INCLUSION` | `P7_RURAL_MAIN`; `P7_RURAL_EXCLUDE_2020_2021`; `P7_RURAL_LAG1`; `P7_AEE_MAIN`; `P7_AEE_EXCLUDE_2020_2021`; `P7_AEE_LAG1` |
| `MF_P8_FINANCING_CAPACITY` | `P8_MAIN_2025_SIZE_ADJUSTED`; `P8_ALT_2024_SIZE_ADJUSTED`; `P8_ALT_2025_PER_ENROLLMENT`; `P8_SENS_2025_TRIMMED_1_PERCENT` |

## Escopo da prova determinística

O digest `b166cd6742cedb279a7c16316245e1ae08589b41c6e73b8cd3849c44fdd22879`
cobre exatamente estes seis artefatos não-manifesto:

| Artefato | SHA-256 |
| --- | --- |
| `RESULTADOS_AA2.csv.gz` | `fd0cabf0f487eefc724b506ddcbc8526d19b141fec42a63fdda24b7f281d971d` |
| `ROBUSTEZ_AA2.csv.gz` | `4af1b3b83d6d4b7a0605df3078f03994da5896acf1360c8b5d8f8ea4ed09f68e` |
| `HETEROGENEIDADE_AA2.csv.gz` | `2502a4572b6e7bca34a0930c8bc4093d8457684129a5dd82cc1f0b6c71692681` |
| `COMPARACOES_ESCOPO_AA2.csv.gz` | `2e1e0cdd8e6fd523f3f069a615d8a5f34d684ab45353aae5c573b7e2329b78e8` |
| `CLAIMS_AA2.json` | `065f4f96d15591b4d239eebb5f18f0f6af0144daec47844dfae00d919fb09419` |
| `QA_SUMMARY_AA2.json` | `678ce5775425260d6521d0558be984667831986fd18c2a8ba47e91dbeef4b9f1` |

Cada candidato registra seu próprio `PYTHONHASHSEED` (`101` ou `202`). O manifesto
final não finge que esses manifestos operacionais são idênticos: registra ambos os
seeds na evidência comum `MULTI_PROCESS_COMMON_EVIDENCE`.

## Testes adicionados ou fortalecidos

1. gate de pré-registro e probe congelados;
2. falha fechada por divergência de um único byte/hash;
3. zero observado preservado e denominador não positivo convertido em indisponível;
4. BH com denominador familiar fixo e fit inválido nulo;
5. fechamento exato da decomposição e denominador populacional positivo;
6. folds e seeds determinísticos sem coerção do código IBGE;
7. grade exata `2^G` de sinais;
8. estimadores de permutação e HC3 finitos;
9. pacote materializado: N/G, primazia de intervalo, bloqueios de P8 e
   heterogeneidade, registry de claims e escopo correto da prova determinística;
10. presença literal das guardas P1/P7/P8 no relatório que alimenta a leitura humana.

## Resultado da reauditoria

O Opus retornou `ON_TRACK` com confiança `0,80` e recomendou a entrada no AA3. Não
identificou rota remanescente de alto impacto para interpretação ou promoção indevida.
As quatro correções documentais baixas pedidas — mapa completo, inventário
determinístico, explicação de `G=496` e recibo documental — foram incorporadas sem
alterar números. O gate AA0 concorrente deve ser repetido em worktree estável, sem
alargar a allowlist AA2.
