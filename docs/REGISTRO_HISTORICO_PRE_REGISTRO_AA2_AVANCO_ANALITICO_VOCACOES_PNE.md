# Registro histórico do pré-registro AA2 — Vocações × PNE

**Classificação:** `DATA_LOGIC`
**Data:** 30 de agosto de 2026
**Finalidade:** tornar auditável a sequência de revisões do desenho AA2 antes da
primeira leitura de `raw_value`.

## Conclusão

O desenho usado para calcular o AA2 é a versão `1.0.3`, SHA-256
`aa931e75a8530bf0f9c22c48b937ef0b92b40210240da012bdb33ed16ff24a25`.
As três revisões Opus do pré-registro terminaram `AT_RISK`; cada rodada foi usada
somente para fechar ambiguidades do desenho antes da geração de resultados. A
sequência local disponível sustenta que as versões `1.0.1`, `1.0.2` e `1.0.3`
precederam o acesso a valores analíticos.

Não existe evidência local recuperável de uma versão `1.0.0`; ela não é inventada
neste histórico. O primeiro artefato identificável é `1.0.1`.

## Sequência preservada

| Ordem | Estado documentado antes de resultados | Evidência local |
| --- | --- | --- |
| 1 | Pré-registro `1.0.1`, `FROZEN_PRE_RESULT`, SHA `f4af4d28cede63a69cdf9df8db95fc72fd353b2de6b4af4f300c4ca873a54f32`; probe sem coeficientes SHA `8bf44d9ec84a92daaa76dfc401fc8e6a6bff09791d8fce5047ee89c4fcba6707` | `.tmp/codex-analytics-program/aa2-opus-prereg-r2/evidence.txt`, SHA `a8f687a8404b08e7b768455ad31e767736749d35c75e9d9b2bd39cba0bb31f59` |
| 2 | Pré-registro `1.0.2`, SHA `828f0b85815f0808e2ee677a7a429539559a0b712d27db6341f1343a31d27012`; registro externo SHA `d222885eba2ffdc1c6ffdc2921b3cac7c6cf7120bc77a3ee4006f25bea820999`; probe final sem valores SHA `070911de9c63c324318679e9cd91e7c065965ad1e934f3d518ad7ce219f3625c` | `.tmp/codex-analytics-program/aa2-opus-prereg-r3/evidence.txt`, SHA `2d1a9c0ebea44882292fe094d8a7818b8651ca312dc56d2fd36f765c70ae83bc` |
| 3 | Pré-registro final `1.0.3`, SHA `aa931e75a8530bf0f9c22c48b937ef0b92b40210240da012bdb33ed16ff24a25`; `firstResultInspected=false` | `docs/PRE_REGISTRO_AA2_AVANCO_ANALITICO_VOCACOES_PNE.json`, cujo `changeLog` registra as três revisões pré-resultado |
| 4 | Alinhamento mecânico do estado externo de `REGISTERED_PRE_RESULT` para o valor exigido pelo contrato, `FROZEN_PRE_RESULT`, ainda com `firstResultInspected=false`; hash final `31a7e733b554f6230863e6cf3efbfa0f4e5389ecdc3a0b2ec359d914714e2c13` | `data_pipeline/contracts/vocacoes-pne-aa2-preregistration-freeze.json` |
| 5 | Gate recompõe os hashes do painel AA1, entrada AA1, ponte curso–CBO, pré-registro, registro externo, contrato, probe e `public/data`; somente depois `load_registered_panel_values()` lê `raw_value` | `verify_preresult_inputs()` e `load_registered_panel_values()` em `data_pipeline/src/vocacoes_pne_advanced_analysis.py` |

## Auditorias Opus pré-resultado

| Rodada | Veredito | SHA-256 do resultado guardado |
| --- | --- | --- |
| inicial | `AT_RISK` | `b4056873863a8399837302934fa5ac8b9aba58f8eb892bfe1c96646396b105bc` |
| fechamento limitado 1 | `AT_RISK` | `5e1a96c5c92d52b807acd2379fcfbe350a1229396f52ac31e0ff914d93a86548` |
| fechamento limitado 2 | `AT_RISK` | `177e0866bcbbf0ec1e50958a48fe013da58b4ac3208420b05c8bf29c41711811` |

Os resultados estão em `.tmp/codex-analytics-program/aa2-opus-prereg*`. Esses
artefatos locais são evidência de auditoria e não entrada de cálculo.

## Limite desta evidência

O trabalho ocorre em um worktree amplo e ainda não commitado. Portanto, não há commit
imutável nem carimbo externo que permita retroativamente uma afirmação mais forte do
que a sequência local de hashes, arquivos de auditoria e gate fail-closed. O registro
externo teve uma correção mecânica de estado antes do primeiro resultado e foi
re-pinado; isso é divulgado, não ocultado.

Para os estágios seguintes, o pré-registro `1.0.3` e o registro externo final são
somente leitura. Qualquer divergência de byte falha antes do carregamento de
`raw_value`. Nenhuma revisão pós-resultado pode ser apresentada como se fosse parte do
pré-registro.
