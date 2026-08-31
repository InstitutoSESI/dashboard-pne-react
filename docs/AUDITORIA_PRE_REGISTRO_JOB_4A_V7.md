# Auditoria de conformidade com o pré-registro — Job 4A V7

## Regra

O pré-registro `1.0.0` permanece congelado e byte a byte inalterado. Esta auditoria compara literalmente o espaço registrado com `run_vocacoes_pne_v7_job3.py`, `models.csv.gz`, `robustness.csv.gz`, `model_failures.json` e os relatórios do Job 3. Ausência no executor não foi reinterpretada retroativamente como inaplicabilidade.

## Itens auditados

| Candidata/item | Classificação | Evidência e consequência |
|---|---|---|
| H2 janela principal 2019–2025 | EXECUTED_AS_PREREGISTERED | 27 modelos principais por 3 etapas × 3 resultados × 3 especificações; os termos de controle elevam o total de linhas, não de modelos. |
| H2 alternativa 2018–2025 | NOT_EXECUTED | O executor corta `stage_frame` em 2019–2025. Rendimento existe em 2018, mas distorção começa em 2019; não houve execução parcial por resultado nem registro de inaplicabilidade. |
| H2 alternativa 2019–2019 | NOT_EXECUTED | Nenhum modelo ou falha registrado. A possível inviabilidade de efeitos fixos em um único ano não foi formalizada antes dos resultados. |
| H2 alternativa 2022–2025 | EXECUTED_AS_PREREGISTERED | Executada apenas para `S1_CLASS_SIZE` em três resultados × três etapas. |
| H2 exclusão 2020–2021 | EXECUTED_AS_PREREGISTERED | Executada apenas para `S1_CLASS_SIZE`; anos efetivos 2019 e 2022–2025. |
| H2 rede | NOT_EXECUTED | Todos os modelos filtram `network=total`; não há sensibilidade por rede. O registro de “network-specific descriptive layers” não substitui o teste modelado. |
| H2 localização | DOCUMENTATION_GAP | A fonte de rendimento é filtrada em `location=total` e a lente escolar está declarada, mas não há comparação urbano/rural nem registro explícito de inaplicabilidade. |
| H2 pesos | NOT_EXECUTED | Todas as 162 especificações têm `weight=unweighted`; não há sensibilidade ponderada. |
| H2 pequeno denominador | NOT_EXECUTED | Nenhuma etiqueta, filtro ou falha correspondente foi materializada. |
| H2 com/sem INSE | DOCUMENTATION_GAP | Só banda larga foi estimada com e sem INSE. Alunos por turma e adequação docente não receberam a especificação “fator + INSE” descrita no pré-registro. |
| H2 conjunto preferido de fatores | NOT_EXECUTED | Não existe especificação multivariada de conjunto preferido com casos completos. |
| H2 lag 0/1 | EXECUTED_AS_PREREGISTERED | Lag 0 cobre as especificações principais; lag 1 foi executado somente para alunos por turma. |
| H2 leave-one-out | DOCUMENTATION_GAP | Foram executadas 90 retiradas: cada um dos dez municípios do Vale removido de cada painel estadual `S1` (3 etapas × 3 resultados). Não houve leave-one-out do modelo `VALE_ONLY`. O resumo chama o método de “Vale-only model sensitivity”, mas H2 não contém sensibilidade `VALE_ONLY`. |
| H2 BH e sem efeitos fixos | EXECUTED_AS_PREREGISTERED | BH foi aplicado à família inteira; o diagnóstico sem efeitos fixos foi executado somente para `S1_CLASS_SIZE`. |
| H3 janela principal 2019–2025 | EXECUTED_AS_PREREGISTERED | RAIS foi modelada como estoque; CAGED permaneceu fluxo descritivo, coerente com o modelo interno pré-registrado. |
| H3 alternativa 2019–2019 | NOT_EXECUTED | Nenhum modelo, falha ou registro pré-resultado de inaplicabilidade. |
| H3 alternativa 2022–2025 | NOT_EXECUTED | Não há `WINDOW_2022_2025`. `EXCLUDE_2020_2021` mantém 2019 e não equivale à janela alternativa. |
| H3 lags 0/1/2 | EXECUTED_AS_PREREGISTERED | Executados para `RAIS 15–17 S1`; as especificações com controle populacional e RAIS 18–24 ficaram apenas em lag 0. |
| H3 controle populacional | EXECUTED_AS_PREREGISTERED | `S2_RAIS_15_17_POPULATION` usa `log_population_15_17`. |
| H3 pesos, INSE e pandemia | EXECUTED_AS_PREREGISTERED | Há `POPULATION_WEIGHTED`, `WITH_INSE` e `EXCLUDE_2020_2021` para `S1`. |
| H3 maiores municípios e pequenos municípios | EXECUTED_AS_PREREGISTERED | `EXCLUDE_LARGEST_RS_10` e `EXCLUDE_SMALL_POPULATION_DECILE` foram executadas. |
| H3 leave-one-out | DOCUMENTATION_GAP | Foram executadas 30 retiradas: cada município do Vale removido do painel estadual `S1` (3 resultados). O resumo também registra `VALE_ONLY`, mas não houve leave-one-out dentro do Vale. |
| H3 CAGED por resultado educacional | EXECUTED_AS_PREREGISTERED | O pré-registro separa estoque RAIS de fluxo CAGED e define o modelo interno para RAIS; CAGED foi usado apenas em fatos municipais. |
| H3 contexto setorial/ocupacional RAIS | DOCUMENTATION_GAP | O relatório do Job 2B descreve o cubo RAIS como contendo CNAE/natureza/tamanho, mas o artefato tem sexo, raça/cor e escolaridade. Setor/ocupação existe no CAGED (fluxo) e no Job 2D (estoque ocupacional geral), não no estoque jovem modelado. |
| A3 pandemia | EXECUTED_WITH_RECORDED_INAPPLICABILITY | `robustness.csv.gz` registra que a oferta detalhada começa em 2023; pandemia não faz parte dos testes A3 pré-registrados. |
| H4 temporal/pandemia/leave-one-out | EXECUTED_WITH_RECORDED_INAPPLICABILITY | O pré-registro define fotografia 2022; o resumo registra explicitamente inaplicabilidade. |

## Contagens leave-one-out efetivamente executadas

- H2: `90` modelos `S1_CLASS_SIZE`, coeficientes preservados em `models.csv.gz`.
- H3: `30` modelos `S1_RAIS_15_17`, coeficientes preservados em `models.csv.gz`.
- H1: `60` resultados (dez municípios × seis etapas), armazenados em `robustness.csv.gz`; método distinto dos painéis H2/H3.
- H4: inaplicável e registrado.
- A3: concentração recalculada e participação dominante registrada; não é retirada modelada.

## Diferença entre pré-registro e executor

Há divergência material: o executor implementou um subconjunto das janelas e sensibilidades H2/H3, sem criar versão nova nem registrar previamente todas as inaplicabilidades. `model_failures.json` está vazio, portanto ausência de modelo não foi tratada como falha executada. O resumo de robustez não apenas omite resultados: em vários casos, os testes não existem no artefato de modelos.
