# Revisão Opus AA1 — painel analítico alinhado

**Classificação:** `DATA_LOGIC`.
**Etapa:** AA1.
**Estado final:** `ON_TRACK_RECONCILED`.

## 1. Escopo da revisão

O usuário autorizou o envio de pacotes textuais delimitados ao Claude Opus 5 para
uma segunda opinião independente. O modelo foi executado pelo wrapper guardado da
skill `opus-verifier`, com esforço máximo, sem fallback e sem acesso direto ao
repositório, às fontes ou a credenciais. Cada rodada recebeu apenas o plano e um
pacote de evidências em UTF-8.

Os artefatos locais das três rodadas estão em:

- `.tmp/codex-analytics-program/aa1-opus`;
- `.tmp/codex-analytics-program/aa1-opus-r2`;
- `.tmp/codex-analytics-program/aa1-opus-r3`.

## 2. Pareceres e decisões

### Rodada 1 — `ON_TRACK`, confiança 0,72

O parecer reconheceu o painel alinhado, o uso exclusivo de rede total na educação,
a preservação de valores ausentes e o não uso de causalidade. Apontou uma lacuna
alta de rastreabilidade sobre o benchmark RS do shift-share e lacunas médias sobre
cobertura parcial, reconciliação do grão e evidência operacional.

A alegação de que totais estaduais estariam misturados ao painel não correspondia ao
estado factual do artefato: só componentes municipais do Vale eram emitidos. A
recomendação foi, porém, aceita como proteção preventiva e resultou nos campos
`reference_scope` e `aggregation_guard`, além do controle que proíbe agregação como
total RS.

### Rodada 2 — `AT_RISK`, confiança 0,72

Uma nova auditoria exigiu dez reforços antes do AA2:

1. razão de cobertura fechada e legível por máquina;
2. reconciliação explícita de fontes naturalmente esparsas;
3. determinismo em processos externos independentes;
4. auditoria temporal das 96 métricas;
5. censo completo de disponibilidade;
6. registro ampliado de QA;
7. evidência executável de ausência de banco e rede;
8. semântica F4 e fechamento do shift-share;
9. vínculo nominal entre sidecars e painel;
10. gate durável e fail-closed para o AA2.

Todos os dez itens foram implementados. A recomendação de uma grade cartesiana
completa foi reenquadrada para uma contabilidade independente de linhas-fonte vezes
regras de expansão: uma grade artificial criaria observações inexistentes em fontes
legitimamente esparsas. A reconciliação resultante fecha 177.265 linhas e 96 métricas
com delta zero.

### Rodada 3 — `ON_TRACK`, confiança 0,72

O terceiro parecer verificou de forma delimitada as dez correções e confirmou que
todas estavam atendidas. Não restou achado alto. Como apêndice de fechamento,
recomendou tornar ainda mais visíveis o censo de indisponibilidade, a invariância
analítica do adendo, a interpretação das assinaturas temporais e o gate do AA2.

## 3. Apêndice aplicado após o parecer final

- cada linha ganhou `unavailability_reason` com vocabulário fechado;
- `QA_SUMMARY_AA1.json` passou a conter o censo reconciliado das 177.265 linhas;
- as 1.379 indisponibilidades foram decompostas em 653 valores-fonte ausentes, 570
  indisponibilidades declaradas e 156 componentes de referência inviáveis por base
  zero;
- a projeção do painel atual nas 26 colunas pré-adendo reproduziu exatamente o
  SHA-256 `1f500c731acecc52ceb2beaee1884a48607ec2f102220b956e5846cc3674fb0a`;
- as 23 métricas com duas assinaturas foram identificadas como universos etários
  paralelos de F3, sem quebra de definição dentro da série;
- `COBERTURA_FAMILIAS_AA1.json` passou a declarar o nome exato do painel;
- `AA2_ENTRY_GATE_AA1.json` passou a integrar o conjunto hashado do pacote e exige
  pré-registro, cinco metadados por linha e escopo `RS_497` para inferência estadual.

Essas mudanças são de rastreabilidade. Nenhum valor, fórmula, universo, lente ou
classificação analítica mudou, fato comprovado pela comparação de hashes e por zero
diferenças analíticas.

## 4. Conclusão reconciliada

O AA1 pode ser encerrado. O rótulo correto é
`RS_ALIGNED_WITH_VALE_DEEP_DIVES`, não um painel integralmente estadual. O AA2 deve
executar o gate antes de inspecionar resultados e deverá preservar resultados
negativos, limites de inferência e a separação entre associação, mecanismo teórico e
causalidade.

Não houve uso de banco, aquisição de dados pela rede ou build completo. A única rede
externa foi a chamada autorizada ao Opus para essas três revisões.
